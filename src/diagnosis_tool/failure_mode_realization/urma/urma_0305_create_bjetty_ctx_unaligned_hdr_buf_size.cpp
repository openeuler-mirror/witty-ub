#include "urma_0305_create_bjetty_ctx_unaligned_hdr_buf_size.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0305CreateBjettyCtxUnalignedHdrBufSize> g_urma("urma_0305");

bool Urma0305CreateBjettyCtxUnalignedHdrBufSize::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Unaligned hdr_buf_size"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0305CreateBjettyCtxUnalignedHdrBufSize::GetName() const
{
    return "create_bjetty_ctx Unaligned hdr_buf_size";
}

std::string Urma0305CreateBjettyCtxUnalignedHdrBufSize::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `hdr_buf_size & (BJETTY_CTX_PAGE_SIZE - 1)`；该路径返回 NULL";
}

RootCause Urma0305CreateBjettyCtxUnalignedHdrBufSize::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0305CreateBjettyCtxUnalignedHdrBufSize::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0305CreateBjettyCtxUnalignedHdrBufSize::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Unaligned hdr_buf_size";
}

std::string Urma0305CreateBjettyCtxUnalignedHdrBufSize::GetId() const
{
    return "urma_0305";
}
} // namespace diag
