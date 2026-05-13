#include "urma_0863_urma_unimport_jfr_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0863UrmaUnimportJfrInvalidParam> g_urma("urma_0863");

bool Urma0863UrmaUnimportJfrInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0863UrmaUnimportJfrInvalidParam::GetName() const
{
    return "urma_unimport_jfr 参数非法";
}

std::string Urma0863UrmaUnimportJfrInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `target_jfr == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0863UrmaUnimportJfrInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0863UrmaUnimportJfrInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0863UrmaUnimportJfrInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0863UrmaUnimportJfrInvalidParam::GetId() const
{
    return "urma_0863";
}
} // namespace diag
