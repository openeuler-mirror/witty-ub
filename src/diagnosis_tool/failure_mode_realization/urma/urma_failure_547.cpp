#include "urma_failure_547.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure547> g_urma("urma_547");

bool UrmaFailure547::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_delete_jetty") != std::string::npos &&
           message.find("ioctl failed, ret:") != std::string::npos && message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure547::GetName() const
{
    return "删除Jetty ioctl驱动命令返回失败";
}

std::string UrmaFailure547::GetRootCauseDesc() const
{
    return "urma_cmd_delete_"
           "jetty通过ioctl向驱动提交删除Jetty命令，驱动侧返回错误或系统调用失败，用户态无法完成对应URMA操作。";
}

RootCause UrmaFailure547::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure547::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure547::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_delete_jetty，ioctl failed, ret:，, errno:。";
}

std::string UrmaFailure547::GetId() const
{
    return "urma_547";
}
} // namespace diag
