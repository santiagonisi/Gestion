#!/bin/bash
gunicorn appy:app --bind 0.0.0.0:$PORT