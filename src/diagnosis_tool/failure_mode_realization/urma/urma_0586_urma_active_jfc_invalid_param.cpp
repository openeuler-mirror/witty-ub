#include "urma_0586_urma_active_jfc_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0586UrmaActiveJfcInvalidParam> g_urma("urma_0586");

bool Urma0586UrmaActiveJfcInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0586UrmaActiveJfcInvalidParam::GetName() const
{
    return "urma_active_jfc 参数非法";
}

std::string Urma0586UrmaActiveJfcInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfc == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0586UrmaActiveJfcInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0586UrmaActiveJfcInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0586UrmaActiveJfcInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0586UrmaActiveJfcInvalidParam::GetId() const
{
    return "urma_0586";
}
} // namespace diag
