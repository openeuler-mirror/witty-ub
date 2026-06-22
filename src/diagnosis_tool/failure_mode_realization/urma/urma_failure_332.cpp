#include "urma_failure_332.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure332> g_urma("urma_332");

bool UrmaFailure332::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_register_seg") != std::string::npos &&
           message.find("ioctl failed in urma_cmd_register_seg, ret:") != std::string::npos &&
           message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure332::GetName() const
{
    return "注册Segment ioctl驱动命令返回失败";
}

std::string UrmaFailure332::GetRootCauseDesc() const
{
    return "urma_cmd_register_"
           "seg通过ioctl向驱动提交注册Segment命令，驱动侧返回错误或系统调用失败，用户态无法完成对应URMA操作。";
}

RootCause UrmaFailure332::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure332::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure332::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_register_seg，ioctl failed in urma_cmd_register_seg, ret:，, "
           "errno:。";
}

std::string UrmaFailure332::GetId() const
{
    return "urma_332";
}
} // namespace diag
