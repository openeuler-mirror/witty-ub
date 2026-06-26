#include "urma_failure_552.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure552> g_urma("urma_552");

bool UrmaFailure552::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_delete_jetty_batch") != std::string::npos &&
           message.find("ioctl failed in urma_cmd_delete_jetty_batch , ret:") != std::string::npos &&
           message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure552::GetName() const
{
    return "删除Jetty ioctl驱动命令返回失败";
}

std::string UrmaFailure552::GetRootCauseDesc() const
{
    return "urma_cmd_delete_jetty_"
           "batch通过ioctl向驱动提交删除Jetty命令，驱动侧返回错误或系统调用失败，用户态无法完成对应URMA操作。";
}

RootCause UrmaFailure552::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure552::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure552::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_delete_jetty_batch，ioctl failed in "
           "urma_cmd_delete_jetty_batch , ret"
           ":，, errno:。";
}

std::string UrmaFailure552::GetId() const
{
    return "urma_552";
}
} // namespace diag
