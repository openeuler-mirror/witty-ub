#include "urma_failure_442.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure442> g_urma("urma_442");

bool UrmaFailure442::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_ioctl_wait_jfc") != std::string::npos &&
           message.find("wait jfc ioctl failed, ret:") != std::string::npos &&
           message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure442::GetName() const
{
    return "wait jfc ioctl驱动命令返回失败";
}

std::string UrmaFailure442::GetRootCauseDesc() const
{
    return "urma_ioctl_wait_jfc通过ioctl向驱动提交wait "
           "jfc命令，驱动侧返回错误或系统调用失败，用户态无法完成对应URMA操作。";
}

RootCause UrmaFailure442::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure442::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure442::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_ioctl_wait_jfc，wait jfc ioctl failed, ret:，, errno:。";
}

std::string UrmaFailure442::GetId() const
{
    return "urma_442";
}
} // namespace diag
