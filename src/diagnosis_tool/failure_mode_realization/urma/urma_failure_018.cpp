#include "urma_failure_018.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure018> g_urma("urma_018");

bool UrmaFailure018::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_write_affinity") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure018::GetName() const
{
    return "dp_ops、post_jfs_wr、target_jfr、dst_tseg无效导致写入affinity失败";
}

std::string UrmaFailure018::GetRootCauseDesc() const
{
    return "urma_write_affinity用于写入affinity，调用方传入的dp_ops、post_jfs_wr、target_jfr、dst_"
           "tseg不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure018::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure018::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure018::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_write_affinity，Invalid parameter.。";
}

std::string UrmaFailure018::GetId() const
{
    return "urma_018";
}
} // namespace diag
