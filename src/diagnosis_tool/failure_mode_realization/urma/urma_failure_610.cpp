#include "urma_failure_610.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure610> g_urma("urma_610");

bool UrmaFailure610::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_modify_jfs") != std::string::npos &&
           message.find("ioctl failed in urma_cmd_modify_jfs, ret:") != std::string::npos &&
           message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure610::GetName() const
{
    return "修改JFS ioctl驱动命令返回失败";
}

std::string UrmaFailure610::GetRootCauseDesc() const
{
    return "urma_cmd_modify_"
           "jfs通过ioctl向驱动提交修改JFS命令，驱动侧返回错误或系统调用失败，用户态无法完成对应URMA操作。";
}

RootCause UrmaFailure610::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure610::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure610::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_modify_jfs，ioctl failed in urma_cmd_modify_jfs, ret:，, "
           "errno:。";
}

std::string UrmaFailure610::GetId() const
{
    return "urma_610";
}
} // namespace diag
