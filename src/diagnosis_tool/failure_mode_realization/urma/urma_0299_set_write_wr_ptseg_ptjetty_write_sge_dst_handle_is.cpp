#include "urma_0299_set_write_wr_ptseg_ptjetty_write_sge_dst_handle_is.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0299SetWriteWrPtsegPtjettyWriteSgeDstHandleIs> g_urma("urma_0299");

bool Urma0299SetWriteWrPtsegPtjettyWriteSgeDstHandleIs::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Write sge.dst->handle is NULL."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0299SetWriteWrPtsegPtjettyWriteSgeDstHandleIs::GetName() const
{
    return "set_write_wr_ptseg_ptjetty Write sge.dst->handle is NULL.（(void *)vtseg->handle == NULL）";
}

std::string Urma0299SetWriteWrPtsegPtjettyWriteSgeDstHandleIs::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `(void *)vtseg->handle == NULL`；该路径返回 URMA_FAIL";
}

RootCause Urma0299SetWriteWrPtsegPtjettyWriteSgeDstHandleIs::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0299SetWriteWrPtsegPtjettyWriteSgeDstHandleIs::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0299SetWriteWrPtsegPtjettyWriteSgeDstHandleIs::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Write sge.dst->handle is NULL.";
}

std::string Urma0299SetWriteWrPtsegPtjettyWriteSgeDstHandleIs::GetId() const
{
    return "urma_0299";
}
} // namespace diag
