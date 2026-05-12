#include "urma_0765_urma_free_jfr_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0765UrmaFreeJfrInvalidParam> g_urma("urma_0765");

bool Urma0765UrmaFreeJfrInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0765UrmaFreeJfrInvalidParam::GetName() const
{
    return "urma_free_jfr 参数非法";
}

std::string Urma0765UrmaFreeJfrInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfr == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0765UrmaFreeJfrInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0765UrmaFreeJfrInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0765UrmaFreeJfrInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0765UrmaFreeJfrInvalidParam::GetId() const
{
    return "urma_0765";
}
} // namespace diag
