#include "urma_failure_432.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure432> g_urma("urma_432");

bool UrmaFailure432::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_deactive_jfc") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure432::GetName() const
{
    return "JFC无效导致去激活JFC失败";
}

std::string UrmaFailure432::GetRootCauseDesc() const
{
    return "urma_cmd_deactive_jfc用于去激活JFC，调用方传入的JFC不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure432::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure432::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure432::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_deactive_jfc，Invalid parameter。";
}

std::string UrmaFailure432::GetId() const
{
    return "urma_432";
}
} // namespace diag
