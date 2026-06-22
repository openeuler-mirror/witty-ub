#include "urma_failure_274.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure274> g_urma("urma_274");

bool UrmaFailure274::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_read") != std::string::npos && message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure274::GetName() const
{
    return "dp_ops、post_jfs_wr、target_jfr、dst_tseg无效导致读取URMA资源失败";
}

std::string UrmaFailure274::GetRootCauseDesc() const
{
    return "urma_read用于读取URMA资源，调用方传入的dp_ops、post_jfs_wr、target_jfr、dst_"
           "tseg不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure274::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure274::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure274::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_read，Invalid parameter.。";
}

std::string UrmaFailure274::GetId() const
{
    return "urma_274";
}
} // namespace diag
