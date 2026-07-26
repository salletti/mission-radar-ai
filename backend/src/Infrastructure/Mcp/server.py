from src.Infrastructure.Mcp.Factory.factory import build_mcp_server

mcp = build_mcp_server()


if __name__ == "__main__":
    mcp.run()  # transport stdio (défaut FastMCP) — requis par les clients locaux
