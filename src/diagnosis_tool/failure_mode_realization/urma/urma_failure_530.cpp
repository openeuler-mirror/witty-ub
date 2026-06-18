#include "urma_failure_530.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure530> g_urma("urma_530");

bool UrmaFailure530::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_free_jfs") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure530::GetName() const
{
    return "JFS无效导致释放JFS失败";
}

std::string UrmaFailure530::GetRootCauseDesc() const
{
    return "urma_cmd_free_jfs用于释放JFS，调用方传入的JFS不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure530::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure530::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure530::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_free_jfs，Invalid parameter。";
}

std::string UrmaFailure530::GetId() const
{
    return "urma_530";
}
} // namespace diag
