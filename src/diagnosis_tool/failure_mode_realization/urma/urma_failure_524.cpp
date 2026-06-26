#include "urma_failure_524.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure524> g_urma("urma_524");

bool UrmaFailure524::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_delete_jfs_batch") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure524::GetName() const
{
    return "jfs_arr、bad_jfs无效导致删除JFS失败";
}

std::string UrmaFailure524::GetRootCauseDesc() const
{
    return "urma_cmd_delete_jfs_batch用于删除JFS，调用方传入的jfs_arr、bad_jfs不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure524::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure524::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure524::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_delete_jfs_batch，Invalid parameter。";
}

std::string UrmaFailure524::GetId() const
{
    return "urma_524";
}
} // namespace diag
