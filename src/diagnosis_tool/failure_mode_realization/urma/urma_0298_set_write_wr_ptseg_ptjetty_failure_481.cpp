#include "urma_0298_set_write_wr_ptseg_ptjetty_failure_481.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0298SetWriteWrPtsegPtjettyFailure481> g_urma("urma_0298");

bool Urma0298SetWriteWrPtsegPtjettyFailure481::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to set ptseg, vtseg is NULL"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0298SetWriteWrPtsegPtjettyFailure481::GetName() const
{
    return "set_write_wr_ptseg_ptjetty 设置属性失败（日志行481）";
}

std::string Urma0298SetWriteWrPtsegPtjettyFailure481::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "URMA_EINVAL";
}

RootCause Urma0298SetWriteWrPtsegPtjettyFailure481::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0298SetWriteWrPtsegPtjettyFailure481::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0298SetWriteWrPtsegPtjettyFailure481::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to set ptseg, vtseg is NULL";
}

std::string Urma0298SetWriteWrPtsegPtjettyFailure481::GetId() const
{
    return "urma_0298";
}
} // namespace diag
