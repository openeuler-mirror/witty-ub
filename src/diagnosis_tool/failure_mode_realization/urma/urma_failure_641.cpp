#include "urma_failure_641.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure641> g_urma("urma_641");

bool UrmaFailure641::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_ioctl_wait_notify") != std::string::npos &&
           message.find("wait notify ioctl failed, ret:") != std::string::npos &&
           message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure641::GetName() const
{
    return "wait notify ioctl驱动命令返回失败";
}

std::string UrmaFailure641::GetRootCauseDesc() const
{
    return "urma_ioctl_wait_notify通过ioctl向驱动提交wait "
           "notify命令，驱动侧返回错误或系统调用失败，用户态无法完成对应URMA操作。";
}

RootCause UrmaFailure641::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure641::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure641::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_ioctl_wait_notify，wait notify ioctl failed, ret:，, errno:。";
}

std::string UrmaFailure641::GetId() const
{
    return "urma_641";
}
} // namespace diag
