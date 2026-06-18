#include "urma_failure_172.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure172> g_urma("urma_172");

bool UrmaFailure172::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_create_jfs") != std::string::npos &&
           message.find("ioctl failed, ret:") != std::string::npos && message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure172::GetName() const
{
    return "创建JFS ioctl驱动命令返回失败";
}

std::string UrmaFailure172::GetRootCauseDesc() const
{
    return "urma_cmd_create_"
           "jfs通过ioctl向驱动提交创建JFS命令，驱动侧返回错误或系统调用失败，用户态无法完成对应URMA操作。";
}

RootCause UrmaFailure172::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure172::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure172::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_create_jfs，ioctl failed, ret:，, errno:。";
}

std::string UrmaFailure172::GetId() const
{
    return "urma_172";
}
} // namespace diag
