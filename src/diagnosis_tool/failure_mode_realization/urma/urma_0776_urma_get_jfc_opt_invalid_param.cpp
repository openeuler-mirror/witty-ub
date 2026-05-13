#include "urma_0776_urma_get_jfc_opt_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0776UrmaGetJfcOptInvalidParam> g_urma("urma_0776");

bool Urma0776UrmaGetJfcOptInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0776UrmaGetJfcOptInvalidParam::GetName() const
{
    return "urma_get_jfc_opt 参数非法";
}

std::string Urma0776UrmaGetJfcOptInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfc == NULL || buf == NULL || opt == 0 || len == 0`；该路径返回 URMA_EINVAL";
}

RootCause Urma0776UrmaGetJfcOptInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0776UrmaGetJfcOptInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0776UrmaGetJfcOptInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0776UrmaGetJfcOptInvalidParam::GetId() const
{
    return "urma_0776";
}
} // namespace diag
