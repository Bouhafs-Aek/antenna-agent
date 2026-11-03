"""Wrapper kept for old command lines: py -3.12 scripts\\analyse.py <out_hfss> --band LO HI (same as `antenna-agent analyse`)."""
from antenna_agent.analyse import main

if __name__ == "__main__":
    main()
