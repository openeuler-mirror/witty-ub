#include "urma_failure_562.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure562> g_urma("urma_562");

bool UrmaFailure562::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_delete_jfs") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure562::GetName() const
{
    return "JFS无效导致删除JFS失败";
}

std::string UrmaFailure562::GetRootCauseDesc() const
{
    return "urma_delete_jfs用于删除JFS，调用方传入的JFS不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure562::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure562::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure562::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jfs，Invalid parameter.。";
}

std::string UrmaFailure562::GetId() const
{
    return "urma_562";
}
} // namespace diag
