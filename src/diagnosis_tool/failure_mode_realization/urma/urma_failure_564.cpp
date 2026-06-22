#include "urma_failure_564.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure564> g_urma("urma_564");

bool UrmaFailure564::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_delete_jfs_batch") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure564::GetName() const
{
    return "jfs_arr、bad_jfs无效导致删除JFS失败";
}

std::string UrmaFailure564::GetRootCauseDesc() const
{
    return "urma_delete_jfs_batch用于删除JFS，调用方传入的jfs_arr、bad_jfs不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure564::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure564::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure564::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jfs_batch，Invalid parameter.。";
}

std::string UrmaFailure564::GetId() const
{
    return "urma_564";
}
} // namespace diag
