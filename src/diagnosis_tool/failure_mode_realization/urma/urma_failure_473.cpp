#include "urma_failure_473.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure473> g_urma("urma_473");

bool UrmaFailure473::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_flush_jfs") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure473::GetName() const
{
    return "JFS、cr无效导致刷新JFS失败";
}

std::string UrmaFailure473::GetRootCauseDesc() const
{
    return "urma_flush_jfs用于刷新JFS，调用方传入的JFS、cr不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure473::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure473::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure473::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_flush_jfs，Invalid parameter.。";
}

std::string UrmaFailure473::GetId() const
{
    return "urma_473";
}
} // namespace diag
