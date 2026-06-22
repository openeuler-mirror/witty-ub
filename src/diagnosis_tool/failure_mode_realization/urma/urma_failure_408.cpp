#include "urma_failure_408.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure408> g_urma("urma_408");

bool UrmaFailure408::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_create_jfc") != std::string::npos &&
           message.find("ioctl failed in urma_cmd_create_jfc, ret:") != std::string::npos &&
           message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure408::GetName() const
{
    return "创建JFC ioctl驱动命令返回失败";
}

std::string UrmaFailure408::GetRootCauseDesc() const
{
    return "urma_cmd_create_"
           "jfc通过ioctl向驱动提交创建JFC命令，驱动侧返回错误或系统调用失败，用户态无法完成对应URMA操作。";
}

RootCause UrmaFailure408::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure408::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure408::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_create_jfc，ioctl failed in urma_cmd_create_jfc, ret:，, "
           "errno:。";
}

std::string UrmaFailure408::GetId() const
{
    return "urma_408";
}
} // namespace diag
