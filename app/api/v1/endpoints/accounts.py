from fastapi import APIRouter, Request

router = APIRouter(prefix="/accounts", tags=["Accounts"])


@router.get("")
async def list_accounts(request: Request) -> list[dict]:
    pool = request.app.state.account_pool
    return await pool.all_accounts()
