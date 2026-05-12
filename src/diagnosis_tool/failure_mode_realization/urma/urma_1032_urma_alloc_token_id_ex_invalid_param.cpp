#include "urma_1032_urma_alloc_token_id_ex_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1032UrmaAllocTokenIdExInvalidParam> g_urma("urma_1032");

bool Urma1032UrmaAllocTokenIdExInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1032UrmaAllocTokenIdExInvalidParam::GetName() const
{
    return "urma_alloc_token_id_ex 参数非法";
}

std::string Urma1032UrmaAllocTokenIdExInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL`；该路径返回 NULL";
}

RootCause Urma1032UrmaAllocTokenIdExInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1032UrmaAllocTokenIdExInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1032UrmaAllocTokenIdExInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma1032UrmaAllocTokenIdExInvalidParam::GetId() const
{
    return "urma_1032";
}
} // namespace diag
