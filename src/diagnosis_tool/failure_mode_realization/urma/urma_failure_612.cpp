#include "urma_failure_612.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure612> g_urma("urma_612");

bool UrmaFailure612::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_query_jfs") != std::string::npos &&
           message.find("ioctl failed, ret:") != std::string::npos && message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure612::GetName() const
{
    return "查询JFS ioctl驱动命令返回失败";
}

std::string UrmaFailure612::GetRootCauseDesc() const
{
    return "urma_cmd_query_"
           "jfs通过ioctl向驱动提交查询JFS命令，驱动侧返回错误或系统调用失败，用户态无法完成对应URMA操作。";
}

RootCause UrmaFailure612::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure612::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure612::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_query_jfs，ioctl failed, ret:，, errno:。";
}

std::string UrmaFailure612::GetId() const
{
    return "urma_612";
}
} // namespace diag
