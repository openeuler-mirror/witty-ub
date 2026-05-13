#include "urma_0938_urma_cmd_get_dmac_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0938UrmaCmdGetDmacInvalidParam> g_urma("urma_0938");

bool Urma0938UrmaCmdGetDmacInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0938UrmaCmdGetDmacInvalidParam::GetName() const
{
    return "urma_cmd_get_dmac 参数非法";
}

std::string Urma0938UrmaCmdGetDmacInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || net_addr == NULL || mac == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0938UrmaCmdGetDmacInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0938UrmaCmdGetDmacInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0938UrmaCmdGetDmacInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0938UrmaCmdGetDmacInvalidParam::GetId() const
{
    return "urma_0938";
}
} // namespace diag
