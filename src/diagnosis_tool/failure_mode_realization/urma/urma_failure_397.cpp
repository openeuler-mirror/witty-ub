#include "urma_failure_397.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure397> g_urma("urma_397");

bool UrmaFailure397::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("convert_jfs_vwr_to_pwr") != std::string::npos &&
           message.find("Unsupported send opcode") != std::string::npos;
}

std::string UrmaFailure397::GetName() const
{
    return "provider未提供convert_jfs_vwr_to_pwr操作实现导致convertconvert、JFS、VWR失败";
}

std::string UrmaFailure397::GetRootCauseDesc() const
{
    return "convert_jfs_vwr_to_"
           "pwr需要通过provider操作表完成convertconvert、JFS、VWR，当前设备provider缺少对应回调或能力不支持该操作。";
}

RootCause UrmaFailure397::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure397::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure397::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：convert_jfs_vwr_to_pwr，Unsupported send opcode。";
}

std::string UrmaFailure397::GetId() const
{
    return "urma_397";
}
} // namespace diag
