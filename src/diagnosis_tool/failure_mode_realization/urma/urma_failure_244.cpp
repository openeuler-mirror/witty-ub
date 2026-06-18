#include "urma_failure_244.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure244> g_urma("urma_244");

bool UrmaFailure244::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_get_jfs_opt") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure244::GetName() const
{
    return "JFS无效导致获取JFS失败";
}

std::string UrmaFailure244::GetRootCauseDesc() const
{
    return "urma_get_jfs_opt用于获取JFS，调用方传入的JFS不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure244::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure244::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure244::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_jfs_opt，Invalid parameter.。";
}

std::string UrmaFailure244::GetId() const
{
    return "urma_244";
}
} // namespace diag
