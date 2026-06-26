#include "urma_failure_631.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure631> g_urma("urma_631");

bool UrmaFailure631::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_active_jetty") != std::string::npos &&
           message.find("ioctl failed in urma_cmd_active_jetty, ret:") != std::string::npos;
}

std::string UrmaFailure631::GetName() const
{
    return "激活Jetty ioctl驱动命令返回失败";
}

std::string UrmaFailure631::GetRootCauseDesc() const
{
    return "urma_cmd_active_"
           "jetty通过ioctl向驱动提交激活Jetty命令，驱动侧返回错误或系统调用失败，用户态无法完成对应URMA操作。";
}

RootCause UrmaFailure631::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure631::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure631::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_active_jetty，ioctl failed in urma_cmd_active_jetty, ret:。";
}

std::string UrmaFailure631::GetId() const
{
    return "urma_631";
}
} // namespace diag
