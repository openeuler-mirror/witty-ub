#include "urma_0809_urma_modify_jfr_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0809UrmaModifyJfrInvalidParam> g_urma("urma_0809");

bool Urma0809UrmaModifyJfrInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0809UrmaModifyJfrInvalidParam::GetName() const
{
    return "urma_modify_jfr 参数非法";
}

std::string Urma0809UrmaModifyJfrInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfr == NULL || attr == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0809UrmaModifyJfrInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0809UrmaModifyJfrInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0809UrmaModifyJfrInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0809UrmaModifyJfrInvalidParam::GetId() const
{
    return "urma_0809";
}
} // namespace diag
