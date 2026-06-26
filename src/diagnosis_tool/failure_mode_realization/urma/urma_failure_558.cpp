#include "urma_failure_558.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure558> g_urma("urma_558");

bool UrmaFailure558::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_deactive_jetty") != std::string::npos &&
           message.find("ioctl failed in urma_cmd_deactive_jetty, ret:") != std::string::npos &&
           message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure558::GetName() const
{
    return "去激活Jetty ioctl驱动命令返回失败";
}

std::string UrmaFailure558::GetRootCauseDesc() const
{
    return "urma_cmd_deactive_"
           "jetty通过ioctl向驱动提交去激活Jetty命令，驱动侧返回错误或系统调用失败，用户态无法完成对应URMA操作。";
}

RootCause UrmaFailure558::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure558::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure558::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_deactive_jetty，ioctl failed in urma_cmd_deactive_jetty, "
           "ret:，, errno"
           ":。";
}

std::string UrmaFailure558::GetId() const
{
    return "urma_558";
}
} // namespace diag
