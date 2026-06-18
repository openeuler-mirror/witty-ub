#include "urma_failure_435.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure435> g_urma("urma_435");

bool UrmaFailure435::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_create_jfce") != std::string::npos &&
           message.find("ioctl failed in urma_cmd_create_jfce, ret:") != std::string::npos &&
           message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure435::GetName() const
{
    return "创建JFCE ioctl驱动命令返回失败";
}

std::string UrmaFailure435::GetRootCauseDesc() const
{
    return "urma_cmd_create_"
           "jfce通过ioctl向驱动提交创建JFCE命令，驱动侧返回错误或系统调用失败，用户态无法完成对应URMA操作。";
}

RootCause UrmaFailure435::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure435::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure435::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_create_jfce，ioctl failed in urma_cmd_create_jfce, ret:，, "
           "errno:。";
}

std::string UrmaFailure435::GetId() const
{
    return "urma_435";
}
} // namespace diag
