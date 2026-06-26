#include "urma_failure_422.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure422> g_urma("urma_422");

bool UrmaFailure422::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_free_jfc") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure422::GetName() const
{
    return "JFC无效导致释放JFC失败";
}

std::string UrmaFailure422::GetRootCauseDesc() const
{
    return "urma_cmd_free_jfc用于释放JFC，调用方传入的JFC不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure422::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure422::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure422::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_free_jfc，Invalid parameter。";
}

std::string UrmaFailure422::GetId() const
{
    return "urma_422";
}
} // namespace diag
