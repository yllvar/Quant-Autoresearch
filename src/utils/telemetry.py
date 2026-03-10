import os
import wandb
from typing import Dict, Any, Optional
from utils.logger import logger

class TelemetryProvider:
    """WandB Telemetry Provider for Quant Autoresearch"""
    
    def __init__(self, project: Optional[str] = None, entity: Optional[str] = None):
        self.api_key = os.getenv("WANDB_API_KEY")
        self.project = project or os.getenv("WANDB_PROJECT", "quant-autoresearch")
        self.entity = entity or os.getenv("WANDB_ENTITY")
        self.enabled = False
        
        if self.api_key:
            try:
                wandb.login(key=self.api_key)
                self.enabled = True
                logger.info("WandB telemetry initialized")
            except Exception as e:
                logger.warning(f"Failed to login to WandB: {e}")
        else:
            logger.info("WandB API key not found. Telemetry disabled.")
            
    def start_run(self, run_name: str, config: Dict[str, Any]):
        """Start a new WandB run"""
        if not self.enabled:
            return
            
        try:
            wandb.init(
                project=self.project,
                entity=self.entity,
                name=run_name,
                config=config
            )
        except Exception as e:
            logger.error(f"Failed to start WandB run: {e}")
            self.enabled = False
            
    def log_metrics(self, metrics: Dict[str, Any], step: Optional[int] = None):
        """Log metrics to WandB"""
        if not self.enabled:
            return
            
        try:
            wandb.log(metrics, step=step)
        except Exception as e:
            logger.warning(f"Failed to log metrics to WandB: {e}")
            
    def finish(self):
        """Finish the WandB run"""
        if self.enabled:
            wandb.finish()

# Global telemetry instance
telemetry = TelemetryProvider()
