#include "urma_failure_170.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure170> g_urma("urma_170");

bool UrmaFailure170::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_create_context") != std::string::npos &&
           message.find("ioctl failed, ret:") != std::string::npos && message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure170::GetName() const
{
    return "创建context ioctl驱动命令返回失败";
}

std::string UrmaFailure170::GetRootCauseDesc() const
{
    return "urma_cmd_create_"
           "context通过ioctl向驱动提交创建context命令，驱动侧返回错误或系统调用失败，用户态无法完成对应URMA操作。";
}

RootCause UrmaFailure170::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure170::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure170::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_create_context，ioctl failed, ret:，, errno:。";
}

std::string UrmaFailure170::GetId() const
{
    return "urma_170";
}
} // namespace diag
