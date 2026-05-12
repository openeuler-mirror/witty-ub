#include "urma_0052_urma_register_log_func_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0052UrmaRegisterLogFuncInvalidParam> g_urma("urma_0052");

bool Urma0052UrmaRegisterLogFuncInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0052UrmaRegisterLogFuncInvalidParam::GetName() const
{
    return "urma_register_log_func 参数非法";
}

std::string Urma0052UrmaRegisterLogFuncInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `func == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0052UrmaRegisterLogFuncInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0052UrmaRegisterLogFuncInvalidParam::GetFixSuggDesc() const
{
    return "当前不会触发失败";
}

std::string Urma0052UrmaRegisterLogFuncInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0052UrmaRegisterLogFuncInvalidParam::GetId() const
{
    return "urma_0052";
}
} // namespace diag
