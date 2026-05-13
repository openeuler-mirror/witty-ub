#include "urma_0942_urma_cmd_get_ip_eid_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0942UrmaCmdGetIpEidInvalidParam> g_urma("urma_0942");

bool Urma0942UrmaCmdGetIpEidInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0942UrmaCmdGetIpEidInvalidParam::GetName() const
{
    return "urma_cmd_get_ip_by_eid 参数非法";
}

std::string Urma0942UrmaCmdGetIpEidInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || eid == NULL || net_addr == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0942UrmaCmdGetIpEidInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0942UrmaCmdGetIpEidInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0942UrmaCmdGetIpEidInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0942UrmaCmdGetIpEidInvalidParam::GetId() const
{
    return "urma_0942";
}
} // namespace diag
