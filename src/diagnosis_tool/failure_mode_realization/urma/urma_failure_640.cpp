#include "urma_failure_640.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure640> g_urma("urma_640");

bool UrmaFailure640::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_ioctl_get_async_event") != std::string::npos &&
           message.find("get async event ioctl failed, ret:") != std::string::npos &&
           message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure640::GetName() const
{
    return "获取异步事件 ioctl驱动命令返回失败";
}

std::string UrmaFailure640::GetRootCauseDesc() const
{
    return "urma_ioctl_get_async_"
           "event通过ioctl向驱动提交获取异步事件命令，驱动侧返回错误或系统调用失败，用户态无法完成对应URMA操作。";
}

RootCause UrmaFailure640::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure640::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure640::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_ioctl_get_async_event，get async event ioctl failed, ret:，, "
           "errno:。";
}

std::string UrmaFailure640::GetId() const
{
    return "urma_640";
}
} // namespace diag
