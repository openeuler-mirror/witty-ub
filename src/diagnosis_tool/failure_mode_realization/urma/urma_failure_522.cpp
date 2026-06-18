#include "urma_failure_522.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure522> g_urma("urma_522");

bool UrmaFailure522::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_delete_jfs") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure522::GetName() const
{
    return "JFS、URMA context、dev_fd无效导致删除JFS失败";
}

std::string UrmaFailure522::GetRootCauseDesc() const
{
    return "urma_cmd_delete_jfs用于删除JFS，调用方传入的JFS、URMA "
           "context、dev_fd不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure522::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure522::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure522::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_delete_jfs，Invalid parameter。";
}

std::string UrmaFailure522::GetId() const
{
    return "urma_522";
}
} // namespace diag
