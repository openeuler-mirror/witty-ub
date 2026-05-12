#include "urma_0954_urma_get_ip_eid_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0954UrmaGetIpEidInvalidParam> g_urma("urma_0954");

bool Urma0954UrmaGetIpEidInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0954UrmaGetIpEidInvalidParam::GetName() const
{
    return "urma_get_ip_by_eid 参数非法";
}

std::string Urma0954UrmaGetIpEidInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || eid == NULL || net_addr == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0954UrmaGetIpEidInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0954UrmaGetIpEidInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0954UrmaGetIpEidInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0954UrmaGetIpEidInvalidParam::GetId() const
{
    return "urma_0954";
}
} // namespace diag
