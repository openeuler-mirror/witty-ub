#include "urma_0277_set_cas_wr_ptseg_pjetty_failure_vtseg_null.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0277SetCasWrPtsegPjettyFailureVtsegNull> g_urma("urma_0277");

bool Urma0277SetCasWrPtsegPjettyFailureVtsegNull::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to set ptseg, vtseg is NULL"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0277SetCasWrPtsegPjettyFailureVtsegNull::GetName() const
{
    return "set_cas_wr_ptseg_pjetty 设置属性失败（vtseg == NULL）";
}

std::string Urma0277SetCasWrPtsegPjettyFailureVtsegNull::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "URMA_EINVAL";
}

RootCause Urma0277SetCasWrPtsegPjettyFailureVtsegNull::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0277SetCasWrPtsegPjettyFailureVtsegNull::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0277SetCasWrPtsegPjettyFailureVtsegNull::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to set ptseg, vtseg is NULL";
}

std::string Urma0277SetCasWrPtsegPjettyFailureVtsegNull::GetId() const
{
    return "urma_0277";
}
} // namespace diag
