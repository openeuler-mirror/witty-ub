#include "urma_failure_750.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure750> g_urma("urma_750");

bool UrmaFailure750::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_write") != std::string::npos && message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure750::GetName() const
{
    return "dp_ops、post_jfs_wr、target_jfr、dst_tseg无效导致写入URMA资源失败";
}

std::string UrmaFailure750::GetRootCauseDesc() const
{
    return "urma_write用于写入URMA资源，调用方传入的dp_ops、post_jfs_wr、target_jfr、dst_"
           "tseg不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure750::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure750::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure750::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_write，Invalid parameter.。";
}

std::string UrmaFailure750::GetId() const
{
    return "urma_750";
}
} // namespace diag
