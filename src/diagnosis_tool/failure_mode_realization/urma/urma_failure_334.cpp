#include "urma_failure_334.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure334> g_urma("urma_334");

bool UrmaFailure334::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_unregister_seg") != std::string::npos &&
           message.find("ioctl failed, ret:") != std::string::npos && message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure334::GetName() const
{
    return "注销Segment ioctl驱动命令返回失败";
}

std::string UrmaFailure334::GetRootCauseDesc() const
{
    return "urma_cmd_unregister_"
           "seg通过ioctl向驱动提交注销Segment命令，驱动侧返回错误或系统调用失败，用户态无法完成对应URMA操作。";
}

RootCause UrmaFailure334::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure334::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure334::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_unregister_seg，ioctl failed, ret:，, errno:。";
}

std::string UrmaFailure334::GetId() const
{
    return "urma_334";
}
} // namespace diag
