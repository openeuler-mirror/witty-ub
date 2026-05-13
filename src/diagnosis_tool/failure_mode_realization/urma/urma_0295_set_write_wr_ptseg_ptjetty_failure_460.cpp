#include "urma_0295_set_write_wr_ptseg_ptjetty_failure_460.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0295SetWriteWrPtsegPtjettyFailure460> g_urma("urma_0295");

bool Urma0295SetWriteWrPtsegPtjettyFailure460::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to set ptseg, vtseg is NULL"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0295SetWriteWrPtsegPtjettyFailure460::GetName() const
{
    return "set_write_wr_ptseg_ptjetty 设置属性失败（日志行460）";
}

std::string Urma0295SetWriteWrPtsegPtjettyFailure460::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "URMA_EINVAL";
}

RootCause Urma0295SetWriteWrPtsegPtjettyFailure460::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0295SetWriteWrPtsegPtjettyFailure460::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0295SetWriteWrPtsegPtjettyFailure460::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to set ptseg, vtseg is NULL";
}

std::string Urma0295SetWriteWrPtsegPtjettyFailure460::GetId() const
{
    return "urma_0295";
}
} // namespace diag
