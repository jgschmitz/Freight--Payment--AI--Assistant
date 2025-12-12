"""
Analytics Service for Freight Payment AI Assistant
"""
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from pymongo import MongoClient
from pymongo.errors import PyMongoError
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans

from config import Settings

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Analytics service for freight payment data analysis"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = MongoClient(settings.mongodb_uri)
        self.db = self.client[settings.mongodb_database]
        self.collection = self.db[settings.mongodb_collection]
    
    async def get_analytics(self) -> Dict[str, Any]:
        """Get comprehensive analytics data"""
        try:
            # Basic statistics
            total_docs = self.collection.count_documents({})
            embedded_docs = self.collection.count_documents({"Reason_Embedded": {"$exists": True}})
            
            # Top reasons analysis
            top_reasons = await self._get_top_reasons()
            
            # Score distribution (placeholder - would need actual search scores)
            score_distribution = await self._get_score_distribution()
            
            # Time-based analytics
            time_analytics = await self._get_time_based_analytics()
            
            return {
                "total_documents": total_docs,
                "embedded_documents": embedded_docs,
                "embedding_percentage": round((embedded_docs / total_docs) * 100, 2) if total_docs > 0 else 0,
                "top_reasons": top_reasons,
                "score_distribution": score_distribution,
                "time_analytics": time_analytics,
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Analytics generation failed: {str(e)}")
            raise
    
    async def _get_top_reasons(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get top reasons by frequency"""
        try:
            pipeline = [
                {"$match": {"event.eventData.subTypeData.reason": {"$exists": True, "$ne": None, "$ne": ""}}},
                {"$group": {
                    "_id": "$event.eventData.subTypeData.reason",
                    "count": {"$sum": 1},
                    "carriers": {"$addToSet": "$event.eventData.carrier"},
                    "statuses": {"$addToSet": "$event.eventData.status"}
                }},
                {"$sort": {"count": -1}},
                {"$limit": limit},
                {"$project": {
                    "reason": "$_id",
                    "count": 1,
                    "carrier_count": {"$size": "$carriers"},
                    "status_count": {"$size": "$statuses"},
                    "_id": 0
                }}
            ]
            
            return list(self.collection.aggregate(pipeline))
            
        except Exception as e:
            logger.error(f"Failed to get top reasons: {str(e)}")
            return []
    
    async def _get_score_distribution(self) -> Dict[str, int]:
        """Get distribution of similarity scores (placeholder implementation)"""
        # This would typically be calculated from actual search results
        # For now, return a sample distribution
        return {
            "0.9-1.0": 150,
            "0.8-0.9": 300,
            "0.7-0.8": 450,
            "0.6-0.7": 200,
            "0.5-0.6": 100,
            "0.0-0.5": 50
        }
    
    async def _get_time_based_analytics(self) -> Dict[str, Any]:
        """Get time-based analytics"""
        try:
            # Get documents with timestamps
            pipeline = [
                {"$match": {"event.timestamp": {"$exists": True}}},
                {"$group": {
                    "_id": {
                        "year": {"$year": "$event.timestamp"},
                        "month": {"$month": "$event.timestamp"},
                        "day": {"$dayOfMonth": "$event.timestamp"}
                    },
                    "count": {"$sum": 1}
                }},
                {"$sort": {"_id.year": -1, "_id.month": -1, "_id.day": -1}},
                {"$limit": 30}
            ]
            
            daily_counts = list(self.collection.aggregate(pipeline))
            
            return {
                "daily_counts": [
                    {
                        "date": f"{item['_id']['year']}-{item['_id']['month']:02d}-{item['_id']['day']:02d}",
                        "count": item["count"]
                    }
                    for item in daily_counts
                ],
                "total_days": len(daily_counts)
            }
            
        except Exception as e:
            logger.error(f"Time-based analytics failed: {str(e)}")
            return {"daily_counts": [], "total_days": 0}
    
    async def get_trends(self, days: int = 30) -> Dict[str, Any]:
        """Get trending patterns over specified number of days"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Trend analysis pipeline
            pipeline = [
                {"$match": {
                    "event.timestamp": {"$gte": cutoff_date},
                    "event.eventData.subTypeData.reason": {"$exists": True, "$ne": None, "$ne": ""}
                }},
                {"$group": {
                    "_id": {
                        "reason": "$event.eventData.subTypeData.reason",
                        "date": {
                            "$dateToString": {
                                "format": "%Y-%m-%d",
                                "date": "$event.timestamp"
                            }
                        }
                    },
                    "count": {"$sum": 1}
                }},
                {"$group": {
                    "_id": "$_id.reason",
                    "total_count": {"$sum": "$count"},
                    "daily_counts": {"$push": {
                        "date": "$_id.date",
                        "count": "$count"
                    }}
                }},
                {"$sort": {"total_count": -1}},
                {"$limit": 10}
            ]
            
            trending_reasons = list(self.collection.aggregate(pipeline))
            
            # Calculate trend direction (simplified)
            for trend in trending_reasons:
                daily_counts = sorted(trend["daily_counts"], key=lambda x: x["date"])
                if len(daily_counts) >= 2:
                    recent_avg = np.mean([d["count"] for d in daily_counts[-7:]])
                    older_avg = np.mean([d["count"] for d in daily_counts[:-7]]) if len(daily_counts) > 7 else recent_avg
                    trend["trend_direction"] = "up" if recent_avg > older_avg else "down" if recent_avg < older_avg else "stable"
                    trend["trend_percentage"] = round(((recent_avg - older_avg) / older_avg * 100) if older_avg > 0 else 0, 2)
                else:
                    trend["trend_direction"] = "stable"
                    trend["trend_percentage"] = 0
            
            return {
                "period_days": days,
                "trending_reasons": trending_reasons,
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Trends analysis failed: {str(e)}")
            return {"period_days": days, "trending_reasons": [], "analysis_timestamp": datetime.utcnow().isoformat()}
    
    async def get_carrier_analytics(self) -> Dict[str, Any]:
        """Get analytics by carrier"""
        try:
            pipeline = [
                {"$match": {"event.eventData.carrier": {"$exists": True, "$ne": None, "$ne": ""}}},
                {"$group": {
                    "_id": "$event.eventData.carrier",
                    "total_events": {"$sum": 1},
                    "unique_reasons": {"$addToSet": "$event.eventData.subTypeData.reason"},
                    "statuses": {"$addToSet": "$event.eventData.status"}
                }},
                {"$project": {
                    "carrier": "$_id",
                    "total_events": 1,
                    "unique_reason_count": {"$size": "$unique_reasons"},
                    "unique_status_count": {"$size": "$statuses"},
                    "_id": 0
                }},
                {"$sort": {"total_events": -1}},
                {"$limit": 20}
            ]
            
            return {
                "carrier_stats": list(self.collection.aggregate(pipeline)),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Carrier analytics failed: {str(e)}")
            return {"carrier_stats": [], "timestamp": datetime.utcnow().isoformat()}
    
    async def perform_clustering_analysis(self, n_clusters: int = 5) -> Dict[str, Any]:
        """Perform clustering analysis on reason texts"""
        try:
            # Get reason texts
            pipeline = [
                {"$match": {"event.eventData.subTypeData.reason": {"$exists": True, "$ne": None, "$ne": ""}}},
                {"$project": {"reason": "$event.eventData.subTypeData.reason", "_id": 0}},
                {"$sample": {"size": 1000}}  # Sample for performance
            ]
            
            reasons = [doc["reason"] for doc in self.collection.aggregate(pipeline)]
            
            if len(reasons) < n_clusters:
                return {"error": "Not enough data for clustering", "reason_count": len(reasons)}
            
            # Vectorize reasons
            vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
            X = vectorizer.fit_transform(reasons)
            
            # Perform clustering
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            cluster_labels = kmeans.fit_predict(X)
            
            # Analyze clusters
            clusters = defaultdict(list)
            for reason, label in zip(reasons, cluster_labels):
                clusters[label].append(reason)
            
            cluster_analysis = []
            for label, cluster_reasons in clusters.items():
                # Get most common words in cluster
                cluster_text = " ".join(cluster_reasons)
                cluster_vectorizer = TfidfVectorizer(max_features=10, stop_words='english')
                cluster_features = cluster_vectorizer.fit_transform([cluster_text])
                top_words = cluster_vectorizer.get_feature_names_out()
                
                cluster_analysis.append({
                    "cluster_id": int(label),
                    "size": len(cluster_reasons),
                    "top_keywords": list(top_words),
                    "sample_reasons": cluster_reasons[:5]
                })
            
            return {
                "clusters": cluster_analysis,
                "total_reasons_analyzed": len(reasons),
                "n_clusters": n_clusters,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Clustering analysis failed: {str(e)}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}
    
    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("Analytics service MongoDB connection closed")