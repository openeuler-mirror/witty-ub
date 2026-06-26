#include "urma_failure_551.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure551> g_urma("urma_551");

bool UrmaFailure551::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_delete_jetty_batch") != std::string::npos &&
           message.find("Failed to malloc buffer.") != std::string::npos;
}

std::string UrmaFailure551::GetName() const
{
    return "uint64分配失败导致删除Jetty失败";
}

std::string UrmaFailure551::GetRootCauseDesc() const
{
    return "urma_cmd_delete_jetty_batch执行删除Jetty前需要准备uint64，内存或资源分配失败会阻断后续URMA操作。";
}

RootCause UrmaFailure551::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure551::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure551::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_delete_jetty_batch，Failed to malloc buffer.。";
}

std::string UrmaFailure551::GetId() const
{
    return "urma_551";
}
} // namespace diag
