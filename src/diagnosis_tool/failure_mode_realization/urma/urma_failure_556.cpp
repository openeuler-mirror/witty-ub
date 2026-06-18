#include "urma_failure_556.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure556> g_urma("urma_556");

bool UrmaFailure556::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_free_jetty") != std::string::npos &&
           message.find("ioctl failed, ret:") != std::string::npos && message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure556::GetName() const
{
    return "释放Jetty ioctl驱动命令返回失败";
}

std::string UrmaFailure556::GetRootCauseDesc() const
{
    return "urma_cmd_free_"
           "jetty通过ioctl向驱动提交释放Jetty命令，驱动侧返回错误或系统调用失败，用户态无法完成对应URMA操作。";
}

RootCause UrmaFailure556::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure556::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure556::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_free_jetty，ioctl failed, ret:，, errno:。";
}

std::string UrmaFailure556::GetId() const
{
    return "urma_556";
}
} // namespace diag
