"""
Runs a model on a single node across multiple gpus.
"""
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
import os
from pathlib import Path
from argparse import ArgumentParser
from LitModel import *
import torch
from pytorch_lightning import Trainer, seed_everything
from pytorch_lightning.callbacks.model_checkpoint import ModelCheckpoint
from pytorch_lightning.loggers import TensorBoardLogger
from pytorch_lightning.callbacks import LearningRateMonitor
from pytorch_lightning.utilities.distributed import rank_zero_only
from pytorch_lightning.callbacks import Callback

seed_everything(1994)

def setup_callbacks_loggers(args):
    
    log_path = Path('/content/logs')
    name = args.backbone
    version = args.version
    tb_logger = TensorBoardLogger(log_path, name=name, version=version)
    lr_logger = LearningRateMonitor(logging_interval='epoch')
    ckpt_callback = ModelCheckpoint(dirpath=Path(tb_logger.log_dir)/'checkpoints/',
    filename='{epoch}-{val_loss:.2f}',
                                    save_top_k=1, save_last=True)
   
    return ckpt_callback, tb_logger, lr_logger


def main(args):
    """ Main training routine specific for this project. """
    
    if args.seed_from_checkpoint:
        print('model seeded')
        model = LitModel.load_from_checkpoint(args.seed_from_checkpoint, **vars(args))
    else:
        model = LitModel(**vars(args))

    ckpt_callback, tb_logger, lr_logger = setup_callbacks_loggers(args)
    
    trainer = Trainer(
                     logger=tb_logger,
                     callbacks=[lr_logger,ckpt_callback],
                     gpus=args.gpus,
                     min_epochs=args.epochs,
                     max_epochs=args.epochs,
                     precision=16,
                     amp_backend='native',
                     val_check_interval=8,
                     distributed_backend='ddp',
                     benchmark=True,
                     sync_batchnorm=True,
                     resume_from_checkpoint=args.resume_from_checkpoint)
    
    
    trainer.logger.log_hyperparams(model.hparams)
    
    # trainer.fit(model)
    trainer.predict(model=model,dataloaders=model.valid_dataset)


def run_cli():
    root_dir = os.path.dirname(os.path.realpath(__file__))
    
    parent_parser = ArgumentParser(add_help=False)

    parser = LitModel.add_model_specific_args(parent_parser)
    
    parser.add_argument('--version',
                         default=None,
                         type=str,
                         metavar='V',
                         help='version or id of the net')
    parser.add_argument('--resume-from-checkpoint',
                         default=None,
                         type=str,
                         metavar='RFC',
                         help='path to checkpoint')
    parser.add_argument('--seed-from-checkpoint',
                         default=None,
                         type=str,
                         metavar='SFC',
                         help='path to checkpoint seed')
    
    args = parser.parse_args()

    main(args)


if __name__ == '__main__':
    run_cli()