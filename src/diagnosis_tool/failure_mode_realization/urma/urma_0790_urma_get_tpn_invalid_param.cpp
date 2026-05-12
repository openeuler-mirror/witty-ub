#include "urma_0790_urma_get_tpn_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0790UrmaGetTpnInvalidParam> g_urma("urma_0790");

bool Urma0790UrmaGetTpnInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0790UrmaGetTpnInvalidParam::GetName() const
{
    return "urma_get_tpn 参数非法";
}

std::string Urma0790UrmaGetTpnInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jetty == NULL`；该路径返回 -URMA_EINVAL";
}

RootCause Urma0790UrmaGetTpnInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0790UrmaGetTpnInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0790UrmaGetTpnInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0790UrmaGetTpnInvalidParam::GetId() const
{
    return "urma_0790";
}
} // namespace diag
