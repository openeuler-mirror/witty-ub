#include "urma_0952_urma_get_eid_ip_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0952UrmaGetEidIpInvalidParam> g_urma("urma_0952");

bool Urma0952UrmaGetEidIpInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0952UrmaGetEidIpInvalidParam::GetName() const
{
    return "urma_get_eid_by_ip 参数非法";
}

std::string Urma0952UrmaGetEidIpInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || net_addr == NULL || eid == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0952UrmaGetEidIpInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0952UrmaGetEidIpInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0952UrmaGetEidIpInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0952UrmaGetEidIpInvalidParam::GetId() const
{
    return "urma_0952";
}
} // namespace diag
