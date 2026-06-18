#include "urma_failure_627.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure627> g_urma("urma_627");

bool UrmaFailure627::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_set_jetty_opt") != std::string::npos &&
           message.find("ioctl failed in urma_cmd_set_jetty_opt, ret:") != std::string::npos &&
           message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure627::GetName() const
{
    return "设置Jetty ioctl驱动命令返回失败";
}

std::string UrmaFailure627::GetRootCauseDesc() const
{
    return "urma_cmd_set_jetty_"
           "opt通过ioctl向驱动提交设置Jetty命令，驱动侧返回错误或系统调用失败，用户态无法完成对应URMA操作。";
}

RootCause UrmaFailure627::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure627::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure627::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_set_jetty_opt，ioctl failed in urma_cmd_set_jetty_opt, ret:，, "
           "errno:。";
}

std::string UrmaFailure627::GetId() const
{
    return "urma_627";
}
} // namespace diag
