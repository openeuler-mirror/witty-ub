#include "urma_failure_185.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure185> g_urma("urma_185");

bool UrmaFailure185::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_create_notifier") != std::string::npos &&
           message.find("ioctl failed in urma_cmd_create_notifier, ret:") != std::string::npos &&
           message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure185::GetName() const
{
    return "创建Notifier ioctl驱动命令返回失败";
}

std::string UrmaFailure185::GetRootCauseDesc() const
{
    return "urma_cmd_create_"
           "notifier通过ioctl向驱动提交创建Notifier命令，驱动侧返回错误或系统调用失败，用户态无法完成对应URMA操作。";
}

RootCause UrmaFailure185::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure185::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure185::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_create_notifier，ioctl failed in urma_cmd_create_notifier, "
           "ret:，, err"
           "no:。";
}

std::string UrmaFailure185::GetId() const
{
    return "urma_185";
}
} // namespace diag
