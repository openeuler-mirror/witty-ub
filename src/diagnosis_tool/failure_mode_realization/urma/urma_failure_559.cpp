#include "urma_failure_559.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure559> g_urma("urma_559");

bool UrmaFailure559::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_free_jfs") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure559::GetName() const
{
    return "provider未提供query_jfs操作实现无效导致释放JFS失败";
}

std::string UrmaFailure559::GetRootCauseDesc() const
{
    return "urma_free_jfs用于释放JFS，调用方传入的provider未提供query_"
           "jfs操作实现不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure559::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure559::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure559::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_free_jfs，Invalid parameter.。";
}

std::string UrmaFailure559::GetId() const
{
    return "urma_559";
}
} // namespace diag
