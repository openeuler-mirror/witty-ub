#include "urma_failure_629.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure629> g_urma("urma_629");

bool UrmaFailure629::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_get_jetty_opt") != std::string::npos &&
           message.find("ioctl failed in urma_cmd_get_jetty_opt, ret:") != std::string::npos &&
           message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure629::GetName() const
{
    return "获取Jetty ioctl驱动命令返回失败";
}

std::string UrmaFailure629::GetRootCauseDesc() const
{
    return "urma_cmd_get_jetty_"
           "opt通过ioctl向驱动提交获取Jetty命令，驱动侧返回错误或系统调用失败，用户态无法完成对应URMA操作。";
}

RootCause UrmaFailure629::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure629::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure629::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_get_jetty_opt，ioctl failed in urma_cmd_get_jetty_opt, ret:，, "
           "errno:。";
}

std::string UrmaFailure629::GetId() const
{
    return "urma_629";
}
} // namespace diag
